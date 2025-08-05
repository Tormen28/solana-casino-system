import requests
import time
import json

# Configuración
BASE_URL = 'http://localhost:5000'
TEST_WALLET = 'CRZ14kNVVeo8GESLa'
TEST_USERNAME = 'Usuario_BGESLa'

def test_user_profile_and_chips():
    """Prueba la carga y sincronización de fichas del usuario"""
    print("=== PRUEBA DE SINCRONIZACIÓN DE FICHAS ===")
    
    # 1. Verificar perfil actual del usuario
    print("\n1. Verificando perfil actual del usuario...")
    response = requests.get(f'{BASE_URL}/api/user/profile/{TEST_WALLET}')
    if response.status_code == 200:
        profile = response.json()
        print(f"   Perfil encontrado: {profile['username']}")
        print(f"   Fichas actuales: {profile['game_tokens']}")
        initial_chips = profile['game_tokens']
    else:
        print(f"   Error al obtener perfil: {response.status_code}")
        return
    
    # 2. Simular cambio de fichas en la base de datos
    print("\n2. Simulando cambio de fichas en la base de datos...")
    new_chips = initial_chips + 500  # Agregar 500 fichas
    update_data = {
        'wallet_address': TEST_WALLET,
        'username': TEST_USERNAME,
        'chips': new_chips
    }
    
    response = requests.post(f'{BASE_URL}/api/user/profile', json=update_data)
    if response.status_code == 200:
        print(f"   Fichas actualizadas a: {new_chips}")
    else:
        print(f"   Error al actualizar fichas: {response.status_code}")
        return
    
    # 3. Verificar que las fichas se actualizaron
    print("\n3. Verificando actualización de fichas...")
    response = requests.get(f'{BASE_URL}/api/user/profile/{TEST_WALLET}')
    if response.status_code == 200:
        profile = response.json()
        print(f"   Fichas después de actualización: {profile['game_tokens']}")
        if profile['game_tokens'] == new_chips:
            print("   ✅ Actualización de fichas exitosa")
        else:
            print(f"   ❌ Error en actualización: esperado {new_chips}, obtenido {profile['game_tokens']}")
    
    # 4. Simular diferentes mesas
    print("\n4. Simulando diferentes tipos de mesa...")
    mesas = [10, 100, 1000]
    
    for mesa in mesas:
        print(f"\n   Mesa de {mesa} fichas:")
        print(f"   - Fichas del usuario: {profile['game_tokens']}")
        print(f"   - Apuesta de la mesa: {mesa}")
        
        if profile['game_tokens'] >= mesa:
            print(f"   ✅ Usuario puede jugar en mesa de {mesa}")
        else:
            print(f"   ❌ Usuario NO puede jugar en mesa de {mesa} (fichas insuficientes)")
    
    # 5. Verificar historial de transacciones
    print("\n5. Verificando historial de transacciones...")
    response = requests.get(f'{BASE_URL}/api/wallet/transactions/{TEST_WALLET}?limit=5&type=games')
    if response.status_code == 200:
        data = response.json()
        transactions = data.get('transactions', [])
        print(f"   Transacciones encontradas: {len(transactions)}")
        if len(transactions) > 0:
            for tx in transactions[-2:]:  # Mostrar las últimas 2
                print(f"   - {tx['transaction_type']}: {tx['amount']} fichas - {tx['description']}")
        else:
            print("   No se encontraron transacciones")
    else:
        print(f"   Error al obtener transacciones: {response.status_code}")
    
    # 6. Verificar balance final
    print("\n6. Verificando balance final...")
    response = requests.get(f'{BASE_URL}/api/user/profile/{TEST_WALLET}')
    if response.status_code == 200:
        final_profile = response.json()
        print(f"   Balance final: {final_profile['game_tokens']} fichas")
        print(f"   Cambio total: {final_profile['game_tokens'] - initial_chips} fichas")
    
    print("\n=== PRUEBA COMPLETADA ===")

if __name__ == '__main__':
    try:
        test_user_profile_and_chips()
    except Exception as e:
        print(f"Error durante la prueba: {e}")