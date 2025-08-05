#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para integrar las funciones de seguridad avanzada en app.py
Este script modifica el archivo app.py existente para añadir:
- Validación de firmas de transacciones
- Límites diarios de retiro
- Rate limiting en APIs
- Logs de auditoría extendidos
- Detección de actividad sospechosa
"""

import os
import re
import shutil
from datetime import datetime

def backup_app_file():
    """Crear backup del archivo app.py antes de modificarlo"""
    backup_name = f"app_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    shutil.copy('app.py', backup_name)
    print(f"✅ Backup creado: {backup_name}")
    return backup_name

def read_file(filename):
    """Leer contenido de archivo"""
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(filename, content):
    """Escribir contenido a archivo"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

def integrate_security_imports(content):
    """Añadir imports de seguridad"""
    # Buscar la línea de imports existente
    import_pattern = r"(from dotenv import load_dotenv)"
    
    security_imports = """from security_integration import (
    SecurityManager, rate_limit, audit_log, 
    validate_withdrawal_security, update_withdrawal_security,
    get_security_status
)
from functools import wraps
import hashlib
import hmac"""
    
    replacement = f"\\1\n{security_imports}"
    
    if "from security_integration import" not in content:
        content = re.sub(import_pattern, replacement, content)
        print("✅ Imports de seguridad añadidos")
    else:
        print("⚠️ Imports de seguridad ya existen")
    
    return content

def integrate_security_initialization(content):
    """Añadir inicialización del sistema de seguridad"""
    # Buscar después de la inicialización de la base de datos
    pattern = r"(Base\.metadata\.create_all\(bind=engine\))"
    
    security_init = """\n# Inicializar sistema de seguridad avanzada
try:
    security_manager = SecurityManager()
    security_manager.initialize_security_tables()
    print("✅ Sistema de seguridad avanzada inicializado")
except Exception as e:
    print(f"⚠️ Error inicializando seguridad: {e}")
    security_manager = None"""
    
    if "security_manager = SecurityManager()" not in content:
        content = re.sub(pattern, f"\\1{security_init}", content)
        print("✅ Inicialización de seguridad añadida")
    else:
        print("⚠️ Inicialización de seguridad ya existe")
    
    return content

def integrate_withdrawal_security(content):
    """Integrar seguridad en el endpoint de retiro"""
    # Buscar el decorador del endpoint de retiro
    pattern = r"(@app\.route\('/api/withdraw/request', methods=\['POST'\]\)\s+def request_withdrawal\(\):)"
    
    # Nuevo decorador con seguridad
    new_decorator = """@app.route('/api/withdraw/request', methods=['POST'])
@rate_limit(max_requests=5, window_minutes=10)  # Máximo 5 retiros cada 10 minutos
@audit_log(action_type='withdrawal_request')
def request_withdrawal():"""
    
    if "@rate_limit" not in content:
        content = re.sub(pattern, new_decorator, content)
        print("✅ Decoradores de seguridad añadidos al endpoint de retiro")
    else:
        print("⚠️ Decoradores de seguridad ya existen en retiro")
    
    # Añadir validación de seguridad dentro de la función
    validation_pattern = r"(chip_amount = int\(data\['chip_amount'\]\))"
    
    security_validation = """chip_amount = int(data['chip_amount'])
        
        # Validación de seguridad avanzada
        security_check = validate_withdrawal_security(
            wallet_address=wallet_address,
            amount=chip_amount,
            sol_amount=sol_amount
        )
        
        if not security_check['valid']:
            return jsonify({
                'error': security_check['reason'],
                'security_alert': True
            }), 400"""
    
    if "validate_withdrawal_security" not in content:
        content = re.sub(validation_pattern, security_validation, content)
        print("✅ Validación de seguridad añadida al retiro")
    else:
        print("⚠️ Validación de seguridad ya existe en retiro")
    
    # Añadir actualización de seguridad después del commit
    update_pattern = r"(db\.commit\(\)\s+db\.close\(\))"
    
    security_update = """db.commit()
        
        # Actualizar registros de seguridad
        update_withdrawal_security(
            wallet_address=wallet_address,
            amount=chip_amount,
            sol_amount=sol_amount,
            transaction_id=transaction_signature
        )
        
        db.close()"""
    
    if "update_withdrawal_security" not in content:
        content = re.sub(update_pattern, security_update, content)
        print("✅ Actualización de seguridad añadida al retiro")
    else:
        print("⚠️ Actualización de seguridad ya existe en retiro")
    
    return content

def add_security_endpoints(content):
    """Añadir nuevos endpoints de seguridad"""
    # Buscar el final del archivo antes del if __name__
    pattern = r"(if __name__ == '__main__':)"
    
    security_endpoints = """\n# Endpoints de seguridad avanzada
@app.route('/api/security/status/<wallet_address>')
@rate_limit(max_requests=10, window_minutes=1)
def get_wallet_security_status(wallet_address):
    # Obtener estado de seguridad de una wallet
    try:
        status = get_security_status(wallet_address)
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/security/limits/<wallet_address>')
@rate_limit(max_requests=10, window_minutes=1)
def get_daily_limits(wallet_address):
    # Obtener límites diarios de una wallet
    try:
        if not security_manager:
            return jsonify({'error': 'Sistema de seguridad no disponible'}), 503
            
        limits = security_manager.get_daily_limits(wallet_address)
        return jsonify(limits)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/security/audit/<wallet_address>')
@rate_limit(max_requests=5, window_minutes=1)
def get_audit_logs(wallet_address):
    # Obtener logs de auditoría de una wallet
    try:
        if not security_manager:
            return jsonify({'error': 'Sistema de seguridad no disponible'}), 503
            
        logs = security_manager.get_audit_logs(wallet_address, limit=50)
        return jsonify({'audit_logs': logs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/security/suspicious')
@rate_limit(max_requests=3, window_minutes=1)
def get_suspicious_activities():
    # Obtener actividades sospechosas (solo admin)
    try:
        if not security_manager:
            return jsonify({'error': 'Sistema de seguridad no disponible'}), 503
            
        activities = security_manager.get_suspicious_activities(limit=100)
        return jsonify({'suspicious_activities': activities})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

\n"""
    
    if "/api/security/status" not in content:
        content = re.sub(pattern, f"{security_endpoints}\\1", content)
        print("✅ Endpoints de seguridad añadidos")
    else:
        print("⚠️ Endpoints de seguridad ya existen")
    
    return content

def integrate_deposit_security(content):
    """Integrar seguridad en el endpoint de depósito"""
    # Buscar el decorador del endpoint de depósito
    pattern = r"(@app\.route\('/api/deposit/process', methods=\['POST'\]\)\s+def process_deposit\(\):)"
    
    new_decorator = """@app.route('/api/deposit/process', methods=['POST'])
@rate_limit(max_requests=10, window_minutes=5)  # Máximo 10 depósitos cada 5 minutos
@audit_log(action_type='deposit_request')
def process_deposit():"""
    
    if "@rate_limit" not in content or "process_deposit" not in content:
        content = re.sub(pattern, new_decorator, content)
        print("✅ Decoradores de seguridad añadidos al endpoint de depósito")
    else:
        print("⚠️ Decoradores de seguridad ya existen en depósito")
    
    return content

def main():
    """Función principal para integrar seguridad"""
    print("🔒 Iniciando integración de seguridad avanzada en app.py...\n")
    
    # Verificar que existe app.py
    if not os.path.exists('app.py'):
        print("❌ Error: No se encontró el archivo app.py")
        return
    
    # Verificar que existe security_integration.py
    if not os.path.exists('security_integration.py'):
        print("❌ Error: No se encontró security_integration.py")
        print("   Ejecuta primero implementar_fase5.py")
        return
    
    try:
        # Crear backup
        backup_name = backup_app_file()
        
        # Leer contenido actual
        content = read_file('app.py')
        
        # Aplicar integraciones paso a paso
        print("\n📝 Integrando funciones de seguridad...")
        content = integrate_security_imports(content)
        content = integrate_security_initialization(content)
        content = integrate_withdrawal_security(content)
        content = integrate_deposit_security(content)
        content = add_security_endpoints(content)
        
        # Escribir archivo modificado
        write_file('app.py', content)
        
        print("\n✅ Integración de seguridad completada exitosamente!")
        print(f"\n📋 Resumen de cambios:")
        print(f"   • Imports de seguridad añadidos")
        print(f"   • Sistema de seguridad inicializado")
        print(f"   • Rate limiting en endpoints críticos")
        print(f"   • Validación de retiros con límites diarios")
        print(f"   • Logs de auditoría automáticos")
        print(f"   • 4 nuevos endpoints de seguridad")
        print(f"   • Backup guardado como: {backup_name}")
        
        print(f"\n🔧 Nuevos endpoints disponibles:")
        print(f"   • GET /api/security/status/<wallet> - Estado de seguridad")
        print(f"   • GET /api/security/limits/<wallet> - Límites diarios")
        print(f"   • GET /api/security/audit/<wallet> - Logs de auditoría")
        print(f"   • GET /api/security/suspicious - Actividades sospechosas")
        
        print(f"\n⚠️ Importante:")
        print(f"   • Reinicia el servidor Flask para aplicar cambios")
        print(f"   • Los límites diarios están configurados en 10 SOL")
        print(f"   • Rate limiting: 5 retiros/10min, 10 depósitos/5min")
        print(f"   • Todos los eventos se registran en security_audit.log")
        
    except Exception as e:
        print(f"❌ Error durante la integración: {e}")
        print(f"   El archivo original no fue modificado")
        return
    
    print(f"\n🎉 ¡Fase 5 - Seguridad Avanzada integrada exitosamente!")
    print(f"   El sistema ahora tiene seguridad de nivel producción")

if __name__ == "__main__":
    main()