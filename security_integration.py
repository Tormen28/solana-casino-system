#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integración de Seguridad para el Sistema de Fichas
Este módulo integra las funciones de seguridad avanzada con los endpoints existentes
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
import logging
from functools import wraps
from collections import defaultdict
import os
from flask import request, jsonify

# Configurar logging
logger = logging.getLogger(__name__)

class SecurityManager:
    """Gestor de seguridad integrado para Flask"""
    
    def __init__(self):
        self.rate_limits = defaultdict(list)
        self.init_security_tables()
    
    def init_security_tables(self):
        """Inicializa tablas de seguridad si no existen"""
        try:
            conn = sqlite3.connect('casino.db')
            cursor = conn.cursor()
            
            # Verificar si las tablas ya existen
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily_limits'")
            if not cursor.fetchone():
                # Crear tablas de seguridad
                cursor.execute('''
                    CREATE TABLE daily_limits (
                        id INTEGER PRIMARY KEY,
                        wallet_address VARCHAR(50) NOT NULL,
                        date DATE NOT NULL,
                        total_withdrawn_sol FLOAT DEFAULT 0,
                        withdrawal_count INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(wallet_address, date)
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE audit_logs (
                        id INTEGER PRIMARY KEY,
                        wallet_address VARCHAR(50),
                        action VARCHAR(50) NOT NULL,
                        details TEXT,
                        ip_address VARCHAR(45),
                        user_agent TEXT,
                        risk_level VARCHAR(20) DEFAULT 'low',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE suspicious_activities (
                        id INTEGER PRIMARY KEY,
                        wallet_address VARCHAR(50),
                        activity_type VARCHAR(50),
                        description TEXT,
                        severity VARCHAR(20) DEFAULT 'medium',
                        status VARCHAR(20) DEFAULT 'pending',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.info("✅ Tablas de seguridad creadas")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error inicializando seguridad: {e}")
    
    def log_audit_event(self, wallet_address, action, details, risk_level='low'):
        """Registra evento de auditoría"""
        try:
            conn = sqlite3.connect('casino.db')
            cursor = conn.cursor()
            
            ip_address = request.remote_addr if request else None
            user_agent = request.headers.get('User-Agent') if request else None
            
            cursor.execute('''
                INSERT INTO audit_logs (wallet_address, action, details, ip_address, user_agent, risk_level)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (wallet_address, action, json.dumps(details), ip_address, user_agent, risk_level))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error en auditoría: {e}")
    
    def check_daily_limits(self, wallet_address, withdrawal_amount_sol):
        """Verifica límites diarios de retiro"""
        try:
            conn = sqlite3.connect('casino.db')
            cursor = conn.cursor()
            
            today = datetime.now().date()
            max_daily_sol = float(os.getenv('MAX_DAILY_WITHDRAW_SOL', 10))
            max_daily_withdrawals = int(os.getenv('MAX_DAILY_WITHDRAWALS', 5))
            
            cursor.execute('''
                SELECT total_withdrawn_sol, withdrawal_count 
                FROM daily_limits 
                WHERE wallet_address = ? AND date = ?
            ''', (wallet_address, today))
            
            result = cursor.fetchone()
            current_withdrawn = result[0] if result else 0
            current_count = result[1] if result else 0
            
            # Verificar límites
            if current_withdrawn + withdrawal_amount_sol > max_daily_sol:
                self.log_audit_event(
                    wallet_address, 
                    'DAILY_LIMIT_EXCEEDED', 
                    {
                        'attempted_amount': withdrawal_amount_sol,
                        'current_withdrawn': current_withdrawn,
                        'daily_limit': max_daily_sol
                    },
                    risk_level='high'
                )
                conn.close()
                return False, f"Límite diario excedido. Máximo: {max_daily_sol} SOL, actual: {current_withdrawn} SOL"
            
            if current_count >= max_daily_withdrawals:
                self.log_audit_event(
                    wallet_address, 
                    'WITHDRAWAL_COUNT_EXCEEDED', 
                    {
                        'current_count': current_count,
                        'daily_limit': max_daily_withdrawals
                    },
                    risk_level='high'
                )
                conn.close()
                return False, f"Límite de retiros diarios excedido. Máximo: {max_daily_withdrawals} retiros"
            
            conn.close()
            return True, "Límites verificados"
            
        except Exception as e:
            logger.error(f"❌ Error verificando límites: {e}")
            return False, "Error interno"
    
    def update_daily_limits(self, wallet_address, withdrawal_amount_sol):
        """Actualiza límites diarios después de retiro exitoso"""
        try:
            conn = sqlite3.connect('casino.db')
            cursor = conn.cursor()
            
            today = datetime.now().date()
            
            cursor.execute('''
                INSERT OR REPLACE INTO daily_limits 
                (wallet_address, date, total_withdrawn_sol, withdrawal_count)
                VALUES (
                    ?, ?, 
                    COALESCE((SELECT total_withdrawn_sol FROM daily_limits WHERE wallet_address = ? AND date = ?), 0) + ?,
                    COALESCE((SELECT withdrawal_count FROM daily_limits WHERE wallet_address = ? AND date = ?), 0) + 1
                )
            ''', (wallet_address, today, wallet_address, today, withdrawal_amount_sol, wallet_address, today))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error actualizando límites: {e}")
    
    def detect_suspicious_activity(self, wallet_address, activity_data):
        """Detecta actividades sospechosas"""
        try:
            current_time = datetime.now()
            
            # Verificar retiros rápidos
            if activity_data.get('type') == 'withdrawal':
                conn = sqlite3.connect('casino.db')
                cursor = conn.cursor()
                
                time_threshold = current_time - timedelta(minutes=5)
                cursor.execute('''
                    SELECT COUNT(*) FROM user_transactions 
                    WHERE wallet_address = ? AND transaction_type = 'withdraw' 
                    AND created_at > ?
                ''', (wallet_address, time_threshold))
                
                recent_withdrawals = cursor.fetchone()[0]
                conn.close()
                
                if recent_withdrawals >= 3:
                    self.report_suspicious_activity(
                        wallet_address, 
                        'rapid_withdrawals',
                        f"Usuario realizó {recent_withdrawals} retiros en 5 minutos",
                        'high'
                    )
                    return True
            
            # Verificar montos grandes
            if activity_data.get('amount', 0) > 5.0:  # Más de 5 SOL
                self.report_suspicious_activity(
                    wallet_address,
                    'large_amount',
                    f"Retiro de monto inusual: {activity_data['amount']} SOL",
                    'medium'
                )
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error detectando actividad sospechosa: {e}")
            return False
    
    def report_suspicious_activity(self, wallet_address, activity_type, description, severity):
        """Reporta actividad sospechosa"""
        try:
            conn = sqlite3.connect('casino.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO suspicious_activities (wallet_address, activity_type, description, severity)
                VALUES (?, ?, ?, ?)
            ''', (wallet_address, activity_type, description, severity))
            
            conn.commit()
            conn.close()
            
            logger.warning(f"🚨 Actividad sospechosa: {activity_type} para {wallet_address}")
            
        except Exception as e:
            logger.error(f"❌ Error reportando actividad sospechosa: {e}")

# Instancia global del gestor de seguridad
security_manager = SecurityManager()

def rate_limit(max_requests=10, window_seconds=60):
    """Decorador para rate limiting"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            client_ip = request.remote_addr
            current_time = time.time()
            
            # Limpiar requests antiguos
            if client_ip in security_manager.rate_limits:
                security_manager.rate_limits[client_ip] = [
                    req_time for req_time in security_manager.rate_limits[client_ip]
                    if current_time - req_time < window_seconds
                ]
            
            # Verificar límite
            if len(security_manager.rate_limits[client_ip]) >= max_requests:
                logger.warning(f"🚫 Rate limit excedido para IP: {client_ip}")
                return jsonify({'error': 'Rate limit excedido', 'retry_after': window_seconds}), 429
            
            # Agregar request actual
            security_manager.rate_limits[client_ip].append(current_time)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def audit_log(action):
    """Decorador para logging de auditoría"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # Extraer wallet_address de los argumentos o request
                wallet_address = None
                if args:
                    wallet_address = args[0] if isinstance(args[0], str) else None
                if not wallet_address and request.json:
                    wallet_address = request.json.get('wallet_address')
                
                # Log exitoso
                security_manager.log_audit_event(
                    wallet_address,
                    action,
                    {
                        'status': 'success',
                        'execution_time': time.time() - start_time,
                        'args': str(args)[:100] if args else None
                    }
                )
                
                return result
                
            except Exception as e:
                # Log error
                wallet_address = None
                if args:
                    wallet_address = args[0] if isinstance(args[0], str) else None
                
                security_manager.log_audit_event(
                    wallet_address,
                    action,
                    {
                        'status': 'error',
                        'error': str(e),
                        'execution_time': time.time() - start_time
                    },
                    risk_level='medium'
                )
                
                raise e
                
        return wrapper
    return decorator

def validate_withdrawal_security(wallet_address, sol_amount):
    """Valida seguridad para retiros"""
    # Verificar límites diarios
    limits_ok, limits_msg = security_manager.check_daily_limits(wallet_address, sol_amount)
    if not limits_ok:
        return False, limits_msg
    
    # Detectar actividades sospechosas
    security_manager.detect_suspicious_activity(wallet_address, {
        'type': 'withdrawal',
        'amount': sol_amount
    })
    
    return True, "Validación exitosa"

def update_withdrawal_security(wallet_address, sol_amount):
    """Actualiza datos de seguridad después de retiro exitoso"""
    security_manager.update_daily_limits(wallet_address, sol_amount)
    
    security_manager.log_audit_event(
        wallet_address,
        'WITHDRAWAL_COMPLETED',
        {
            'amount_sol': sol_amount,
            'timestamp': datetime.now().isoformat()
        }
    )

# Funciones de utilidad para endpoints
def get_security_status():
    """Obtiene estado del sistema de seguridad"""
    try:
        conn = sqlite3.connect('casino.db')
        cursor = conn.cursor()
        
        # Contar logs de auditoría del día
        today = datetime.now().date()
        cursor.execute('''
            SELECT COUNT(*) FROM audit_logs 
            WHERE DATE(created_at) = ?
        ''', (today,))
        daily_logs = cursor.fetchone()[0]
        
        # Contar actividades sospechosas pendientes
        cursor.execute('''
            SELECT COUNT(*) FROM suspicious_activities 
            WHERE status = 'pending'
        ''', )
        pending_suspicious = cursor.fetchone()[0]
        
        # Obtener límites diarios activos
        cursor.execute('''
            SELECT COUNT(*) FROM daily_limits 
            WHERE date = ?
        ''', (today,))
        active_limits = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'security_enabled': True,
            'daily_audit_logs': daily_logs,
            'pending_suspicious_activities': pending_suspicious,
            'active_daily_limits': active_limits,
            'rate_limiting_active': True,
            'last_check': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estado de seguridad: {e}")
        return {
            'security_enabled': False,
            'error': str(e)
        }