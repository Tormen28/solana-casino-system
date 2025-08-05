#!/usr/bin/env python3
"""
Script de prueba para verificar que los nuevos usuarios reciben 100 fichas al registrarse
"""

import requests
import json
import random
import string

def generate_fake_wallet():
    """Genera una dirección de wallet falsa para pruebas"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=44))

def test_user_registration():
    """Prueba el registro de un nuevo usuario"""
    base_url = 'http://localhost:5000'
    fake_wallet = generate_fake_wallet()
    
    print(f"🧪 Probando registro de usuario con wallet: {fake_wallet[:8]}...")
    
    try:
        # Hacer petición para obtener/crear perfil de usuario
        response = requests.get(f'{base_url}/api/user/profile/{fake_wallet}')
        
        if response.status_code == 200:
            profile_data = response.json()
            print("✅ Usuario registrado exitosamente!")
            print(f"📊 Datos del perfil:")
            print(f"   - Wallet: {profile_data['wallet_address'][:8]}...")
            print(f"   - Username: {profile_data['username']}")
            print(f"   - Fichas iniciales: {profile_data['game_tokens']}")
            print(f"   - Juegos totales: {profile_data['total_games']}")
            print(f"   - Victorias totales: {profile_data['total_wins']}")
            
            # Verificar que las fichas iniciales sean 100
            if profile_data['game_tokens'] == 100:
                print("✅ ¡Correcto! El usuario recibió 100 fichas iniciales")
                return True
            else:
                print(f"❌ Error: Se esperaban 100 fichas, pero recibió {profile_data['game_tokens']}")
                return False
        else:
            print(f"❌ Error en la petición: {response.status_code}")
            print(f"Respuesta: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: No se pudo conectar al servidor. ¿Está ejecutándose en localhost:5000?")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Iniciando prueba de registro de usuario...")
    print("=" * 50)
    
    success = test_user_registration()
    
    print("=" * 50)
    if success:
        print("🎉 ¡Prueba exitosa! El sistema de registro funciona correctamente.")
    else:
        print("💥 Prueba fallida. Revisa la configuración del servidor.")