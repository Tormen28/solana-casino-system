#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Solución Final para el Sistema de Depósitos
Configura el sistema para funcionar localmente y proporciona guía completa
"""

import os
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv, set_key

# Cargar variables de entorno
load_dotenv()

class SolucionFinal:
    def __init__(self):
        self.env_file = '.env'
        
    def verificar_estado_actual(self):
        """Verifica el estado actual del sistema"""
        print("🔍 VERIFICANDO ESTADO ACTUAL DEL SISTEMA")
        print("=" * 50)
        
        # Variables de entorno
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
        
        print("📊 COMPONENTES DEL SISTEMA:")
        for componente, configurado in estado.items():
            status = "✅" if configurado else "❌"
            nombre = componente.replace('_', ' ').title()
            print(f"  {status} {nombre}")
            
        configurados = sum(estado.values())
        total = len(estado)
        porcentaje = (configurados / total) * 100
        
        print(f"\n📈 Configuración: {porcentaje:.0f}% completa ({configurados}/{total})")
        
        return estado, porcentaje
        
    def verificar_servidor_flask(self):
        """Verifica si Flask está ejecutándose"""
        try:
            response = requests.get('http://localhost:5000/api/webhook/status', timeout=3)
            return response.status_code == 200
        except:
            return False
            
    def configurar_para_desarrollo(self):
        """Configura el sistema para desarrollo local"""
        print("\n🔧 CONFIGURANDO PARA DESARROLLO LOCAL")
        print("=" * 50)
        
        # Configurar webhook URL para desarrollo
        webhook_url = "http://localhost:5000/api/webhook/helius"
        set_key(self.env_file, 'WEBHOOK_URL', webhook_url)
        print(f"✅ WEBHOOK_URL configurada para desarrollo: {webhook_url}")
        
        # Verificar otras configuraciones
        custodial_key = os.getenv('CUSTODIAL_PRIVATE_KEY')
        if custodial_key == 'YOUR_CUSTODIAL_PRIVATE_KEY_BASE58_HERE':
            print("⚠️ CUSTODIAL_PRIVATE_KEY aún no configurada")
            print("   Esta es necesaria para procesar retiros automáticos")
            
        return True
        
    def probar_procesamiento_manual(self):
        """Prueba el procesamiento manual de depósitos"""
        print("\n🧪 PROBANDO PROCESAMIENTO MANUAL")
        print("=" * 50)
        
        # Verificar que existe el script de procesamiento manual
        if os.path.exists('process_deposit.py'):
            print("✅ Script de procesamiento manual disponible")
            print("💡 Puedes usar 'python process_deposit.py' para procesar depósitos manualmente")
        else:
            print("❌ Script de procesamiento manual no encontrado")
            
        # Verificar base de datos
        try:
            import sqlite3
            conn = sqlite3.connect('casino.db')
            cursor = conn.cursor()
            
            # Verificar tablas
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tablas = [row[0] for row in cursor.fetchall()]
            
            if 'user_transactions' in tablas and 'user_profiles' in tablas:
                print("✅ Base de datos configurada correctamente")
                
                # Mostrar estadísticas
                cursor.execute("SELECT COUNT(*) FROM user_profiles")
                usuarios = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM user_transactions")
                transacciones = cursor.fetchone()[0]
                
                print(f"📊 Usuarios registrados: {usuarios}")
                print(f"📊 Transacciones registradas: {transacciones}")
            else:
                print("❌ Tablas de base de datos no encontradas")
                
            conn.close()
            
        except Exception as e:
            print(f"❌ Error verificando base de datos: {e}")
            
    def generar_guia_completa(self, estado):
        """Genera una guía completa para usar el sistema"""
        print("\n" + "=" * 60)
        print("📚 GUÍA COMPLETA DEL SISTEMA")
        print("=" * 60)
        
        print("\n🎯 ESTADO ACTUAL:")
        if estado['helius_api_key'] and estado['custodial_address'] and estado['servidor_flask']:
            print("✅ Sistema base configurado y funcionando")
            print("✅ Puede recibir y procesar depósitos")
            
            if estado['custodial_private_key']:
                print("✅ Puede procesar retiros automáticamente")
            else:
                print("⚠️ Retiros requieren configuración adicional")
                
            if estado['webhook_url']:
                print("✅ Webhooks configurados (desarrollo)")
            else:
                print("⚠️ Webhooks requieren configuración")
        else:
            print("❌ Sistema requiere configuración adicional")
            
        print("\n🔄 CÓMO FUNCIONA ACTUALMENTE:")
        print("1. DEPÓSITOS MANUALES:")
        print("   • Usar: python process_deposit.py")
        print("   • Procesa transacciones pendientes")
        print("   • Actualiza balances automáticamente")
        
        print("\n2. DEPÓSITOS AUTOMÁTICOS (requiere configuración):")
        print("   • Instalar ngrok: https://ngrok.com/download")
        print("   • Ejecutar: ngrok http 5000")
        print("   • Configurar WEBHOOK_URL con la URL de ngrok")
        print("   • El sistema procesará depósitos automáticamente")
        
        print("\n3. RETIROS (requiere clave privada):")
        print("   • Configurar CUSTODIAL_PRIVATE_KEY en .env")
        print("   • El sistema procesará retiros automáticamente")
        
        print("\n🛠️ PASOS PARA CONFIGURACIÓN COMPLETA:")
        
        if not estado['custodial_private_key']:
            print("\n🔐 PASO 1: Configurar Clave Privada Custodial")
            print("   1. Abrir archivo .env")
            print("   2. Buscar: CUSTODIAL_PRIVATE_KEY=YOUR_CUSTODIAL_PRIVATE_KEY_BASE58_HERE")
            print("   3. Reemplazar con la clave privada real")
            print("   4. Guardar archivo")
            print("   ⚠️ CRÍTICO: Sin esta clave no se pueden procesar retiros")
            
        print("\n🌐 PASO 2: Configurar Webhooks Automáticos (Opcional)")
        print("   1. Descargar ngrok: https://ngrok.com/download")
        print("   2. Instalar ngrok")
        print("   3. Ejecutar: ngrok http 5000")
        print("   4. Copiar URL HTTPS (ej: https://abc123.ngrok.io)")
        print("   5. Actualizar WEBHOOK_URL en .env")
        print("   6. Reiniciar servidor Flask")
        print("   💡 Esto permite depósitos automáticos en tiempo real")
        
        print("\n🧪 PASO 3: Probar el Sistema")
        print("   1. Enviar 0.001 SOL a la dirección custodial:")
        print(f"      {os.getenv('CUSTODIAL_ADDRESS')}")
        print("   2. Si webhooks están configurados: esperar ~30 segundos")
        print("   3. Si no: ejecutar 'python process_deposit.py'")
        print("   4. Verificar que se agregaron chips al balance")
        
        print("\n📁 ARCHIVOS IMPORTANTES:")
        archivos = {
            '.env': 'Configuración del sistema',
            'app.py': 'Servidor principal Flask',
            'process_deposit.py': 'Procesamiento manual de depósitos',
            'casino.db': 'Base de datos SQLite',
            'configuracion_reporte.json': 'Último reporte de configuración'
        }
        
        for archivo, descripcion in archivos.items():
            existe = "✅" if os.path.exists(archivo) else "❌"
            print(f"   {existe} {archivo} - {descripcion}")
            
        print("\n🔧 COMANDOS ÚTILES:")
        comandos = [
            "python app.py - Iniciar servidor principal",
            "python process_deposit.py - Procesar depósitos manualmente",
            "curl http://localhost:5000/api/webhook/status - Ver estado del sistema",
            "ngrok http 5000 - Crear túnel público para webhooks"
        ]
        
        for comando in comandos:
            print(f"   • {comando}")
            
    def ejecutar_solucion_final(self):
        """Ejecuta la solución final completa"""
        print("🎯 SOLUCIÓN FINAL DEL SISTEMA DE DEPÓSITOS")
        print("=" * 60)
        print(f"Ejecutado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Verificar estado actual
        estado, porcentaje = self.verificar_estado_actual()
        
        # Configurar para desarrollo
        self.configurar_para_desarrollo()
        
        # Probar procesamiento manual
        self.probar_procesamiento_manual()
        
        # Generar guía completa
        self.generar_guia_completa(estado)
        
        # Guardar reporte final
        reporte = {
            'timestamp': datetime.now().isoformat(),
            'tipo': 'solucion_final',
            'porcentaje_completitud': porcentaje,
            'estado_componentes': estado,
            'configuracion_desarrollo': True,
            'procesamiento_manual_disponible': os.path.exists('process_deposit.py'),
            'base_datos_disponible': os.path.exists('casino.db'),
            'recomendaciones': [
                'Configurar CUSTODIAL_PRIVATE_KEY para retiros automáticos',
                'Instalar ngrok para webhooks automáticos',
                'Probar con transacción pequeña (0.001 SOL)'
            ]
        }
        
        with open('solucion_final_reporte.json', 'w', encoding='utf-8') as f:
            json.dump(reporte, f, indent=2, ensure_ascii=False)
            
        print(f"\n💾 Reporte completo guardado en: solucion_final_reporte.json")
        
        # Mensaje final
        if porcentaje >= 60:
            print("\n🎉 ¡SISTEMA FUNCIONAL!")
            print("El sistema puede procesar depósitos. Sigue la guía para configuración completa.")
        else:
            print("\n⚠️ SISTEMA REQUIERE CONFIGURACIÓN")
            print("Revisa la guía anterior para completar la configuración.")
            
if __name__ == '__main__':
    solucion = SolucionFinal()
    solucion.ejecutar_solucion_final()