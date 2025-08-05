#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración Automática del Sistema de Depósitos
Configura automáticamente todos los componentes sin interacción del usuario
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

class ConfiguracionAutomatica:
    def __init__(self):
        self.env_file = '.env'
        self.resultados = []
        self.errores = []
        
    def log(self, mensaje, tipo="info"):
        """Registra un mensaje con timestamp"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        if tipo == "success":
            print(f"[{timestamp}] ✅ {mensaje}")
        elif tipo == "error":
            print(f"[{timestamp}] ❌ {mensaje}")
        elif tipo == "warning":
            print(f"[{timestamp}] ⚠️ {mensaje}")
        else:
            print(f"[{timestamp}] ℹ️ {mensaje}")
            
    def verificar_ngrok(self):
        """Verifica si ngrok está disponible y configurado"""
        self.log("Verificando ngrok...")
        
        try:
            # Verificar si ngrok está instalado
            result = subprocess.run(['ngrok', 'version'], capture_output=True, text=True)
            if result.returncode != 0:
                self.log("ngrok no está instalado", "warning")
                return None
                
            # Verificar si hay túneles activos
            try:
                response = requests.get('http://localhost:4040/api/tunnels', timeout=3)
                if response.status_code == 200:
                    tunnels = response.json().get('tunnels', [])
                    
                    for tunnel in tunnels:
                        if tunnel.get('proto') == 'https' and '5000' in tunnel.get('config', {}).get('addr', ''):
                            webhook_url = tunnel['public_url'] + '/api/webhook/helius'
                            self.log(f"Túnel ngrok encontrado: {webhook_url}", "success")
                            return webhook_url
                            
            except requests.exceptions.ConnectionError:
                pass
                
            self.log("ngrok instalado pero sin túneles activos", "warning")
            return None
            
        except Exception as e:
            self.log(f"Error verificando ngrok: {e}", "error")
            return None
            
    def configurar_webhook_url(self):
        """Configura la URL del webhook automáticamente"""
        self.log("Configurando URL del webhook...")
        
        # Verificar configuración actual
        current_url = os.getenv('WEBHOOK_URL')
        if current_url and current_url != 'https://tu-dominio.com/webhook':
            self.log(f"WEBHOOK_URL ya configurada: {current_url}", "success")
            self.resultados.append("WEBHOOK_URL ya configurada")
            return True
            
        # Intentar detectar ngrok
        webhook_url = self.verificar_ngrok()
        
        if webhook_url:
            set_key(self.env_file, 'WEBHOOK_URL', webhook_url)
            self.log(f"WEBHOOK_URL configurada automáticamente: {webhook_url}", "success")
            self.resultados.append("WEBHOOK_URL configurada con ngrok")
            return True
        else:
            # Configurar URL de desarrollo local
            dev_url = "https://tu-servidor.ngrok.io/api/webhook/helius"
            set_key(self.env_file, 'WEBHOOK_URL', dev_url)
            self.log("WEBHOOK_URL configurada con placeholder", "warning")
            self.resultados.append("WEBHOOK_URL configurada (requiere actualización manual)")
            return False
            
    def verificar_servidor_flask(self):
        """Verifica si el servidor Flask está ejecutándose"""
        try:
            response = requests.get('http://localhost:5000/api/webhook/status', timeout=3)
            return response.status_code == 200
        except:
            return False
            
    def configurar_webhook_helius(self):
        """Configura el webhook en Helius si es posible"""
        self.log("Configurando webhook en Helius...")
        
        webhook_url = os.getenv('WEBHOOK_URL')
        if not webhook_url or webhook_url == 'https://tu-dominio.com/webhook':
            self.log("WEBHOOK_URL no válida, omitiendo configuración de Helius", "warning")
            return False
            
        if not self.verificar_servidor_flask():
            self.log("Servidor Flask no está ejecutándose", "warning")
            self.log("Ejecuta 'python app.py' para habilitar la configuración automática", "info")
            return False
            
        try:
            webhook_data = {'webhook_url': webhook_url}
            response = requests.post(
                'http://localhost:5000/api/webhook/setup',
                json=webhook_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                self.log(f"Webhook configurado en Helius exitosamente", "success")
                self.resultados.append("Webhook configurado en Helius")
                return True
            else:
                error_data = response.json()
                self.log(f"Error configurando webhook: {error_data.get('error')}", "error")
                return False
                
        except Exception as e:
            self.log(f"Error configurando webhook en Helius: {e}", "error")
            return False
            
    def verificar_configuracion_completa(self):
        """Verifica el estado final de la configuración"""
        self.log("Verificando configuración completa...")
        
        # Verificar variables de entorno críticas
        helius_key = os.getenv('HELIUS_API_KEY')
        custodial_address = os.getenv('CUSTODIAL_ADDRESS')
        custodial_key = os.getenv('CUSTODIAL_PRIVATE_KEY')
        webhook_url = os.getenv('WEBHOOK_URL')
        
        estado = {
            'helius_api_key': bool(helius_key and helius_key != 'your_helius_api_key_here'),
            'custodial_address': bool(custodial_address),
            'custodial_private_key': bool(custodial_key and custodial_key != 'YOUR_CUSTODIAL_PRIVATE_KEY_BASE58_HERE'),
            'webhook_url': bool(webhook_url and webhook_url != 'https://tu-dominio.com/webhook'),
            'servidor_flask': self.verificar_servidor_flask()
        }
        
        self.log("Estado de la configuración:", "info")
        for componente, configurado in estado.items():
            status = "✅" if configurado else "❌"
            self.log(f"  {componente}: {status}")
            
        # Calcular porcentaje de completitud
        total = len(estado)
        configurados = sum(estado.values())
        porcentaje = (configurados / total) * 100
        
        self.log(f"Configuración completa: {porcentaje:.0f}% ({configurados}/{total})", "info")
        
        return estado, porcentaje
        
    def generar_instrucciones_pendientes(self, estado):
        """Genera instrucciones para completar la configuración"""
        instrucciones = []
        
        if not estado['custodial_private_key']:
            instrucciones.append({
                'paso': 'Configurar CUSTODIAL_PRIVATE_KEY',
                'descripcion': 'Agregar la clave privada de la wallet custodial en el archivo .env',
                'comando': 'Editar .env y reemplazar YOUR_CUSTODIAL_PRIVATE_KEY_BASE58_HERE'
            })
            
        if not estado['webhook_url'] or not self.verificar_ngrok():
            instrucciones.append({
                'paso': 'Configurar túnel ngrok',
                'descripcion': 'Crear túnel público para recibir webhooks',
                'comando': 'ngrok http 5000'
            })
            
        if not estado['servidor_flask']:
            instrucciones.append({
                'paso': 'Iniciar servidor Flask',
                'descripcion': 'Ejecutar la aplicación principal',
                'comando': 'python app.py'
            })
            
        return instrucciones
        
    def ejecutar_configuracion(self):
        """Ejecuta la configuración automática completa"""
        print("🔧 CONFIGURACIÓN AUTOMÁTICA DEL SISTEMA")
        print("=" * 50)
        print(f"Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        # Paso 1: Configurar URL del webhook
        self.configurar_webhook_url()
        
        # Paso 2: Configurar webhook en Helius (si es posible)
        self.configurar_webhook_helius()
        
        # Paso 3: Verificar configuración completa
        estado, porcentaje = self.verificar_configuracion_completa()
        
        # Paso 4: Generar instrucciones pendientes
        instrucciones = self.generar_instrucciones_pendientes(estado)
        
        # Reporte final
        print("\n" + "=" * 50)
        print("📊 REPORTE FINAL")
        print("=" * 50)
        
        if self.resultados:
            print(f"\n✅ CONFIGURACIONES COMPLETADAS ({len(self.resultados)}):")
            for i, resultado in enumerate(self.resultados, 1):
                print(f"  {i}. {resultado}")
                
        if instrucciones:
            print(f"\n📋 PASOS PENDIENTES ({len(instrucciones)}):")
            for i, instruccion in enumerate(instrucciones, 1):
                print(f"  {i}. {instruccion['paso']}")
                print(f"     {instruccion['descripcion']}")
                print(f"     Comando: {instruccion['comando']}")
                print()
                
        if porcentaje >= 80:
            print("🎉 ¡SISTEMA CASI LISTO!")
            print("Solo faltan algunos pasos menores para completar la configuración.")
        elif porcentaje >= 60:
            print("⚠️ SISTEMA PARCIALMENTE CONFIGURADO")
            print("Se requieren algunos pasos adicionales.")
        else:
            print("❌ SISTEMA REQUIERE CONFIGURACIÓN ADICIONAL")
            print("Se necesitan varios pasos para completar la configuración.")
            
        # Guardar reporte
        reporte = {
            'timestamp': datetime.now().isoformat(),
            'porcentaje_completitud': porcentaje,
            'estado_componentes': estado,
            'configuraciones_completadas': self.resultados,
            'instrucciones_pendientes': instrucciones,
            'errores': self.errores
        }
        
        with open('configuracion_reporte.json', 'w', encoding='utf-8') as f:
            json.dump(reporte, f, indent=2, ensure_ascii=False)
            
        print(f"\n💾 Reporte detallado guardado en: configuracion_reporte.json")
        print("\n🔄 Para aplicar cambios, reinicia el servidor Flask después de completar los pasos pendientes.")
        
if __name__ == '__main__':
    configurador = ConfiguracionAutomatica()
    configurador.ejecutar_configuracion()