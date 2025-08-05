import sqlite3
import datetime

def process_manual_deposit():
    conn = sqlite3.connect('game.db')
    cursor = conn.cursor()
    
    wallet_address = 'CR2Z14kNMeaLpfD8HmEL5Z6Nb1vYJXzxWBEQeoBGESLa'
    signature = '2pXinbjojK5ZEzRqzMxAgKskBiWZuMce6mxhBmLVYi3AFeiYAToqbKx2gvv1Lus7YtjU5bC4YCnMYpCaov6zcTXh'
    amount = 1.0
    chips_to_add = 1000  # 1 SOL = 1000 fichas
    
    try:
        # Verificar si el usuario existe
        cursor.execute('SELECT chips FROM user_profiles WHERE wallet_address = ?', (wallet_address,))
        user = cursor.fetchone()
        
        if user:
            current_chips = user[0]
            new_chips = current_chips + chips_to_add
            
            # Actualizar fichas del usuario
            cursor.execute('UPDATE user_profiles SET chips = ? WHERE wallet_address = ?', 
                         (new_chips, wallet_address))
            
            # Registrar la transacción
            cursor.execute('''
                INSERT INTO user_transactions (wallet_address, transaction_type, amount, signature, status, created_at) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (wallet_address, 'deposit', amount, signature, 'completed', datetime.datetime.now()))
            
            conn.commit()
            
            print(f'✅ DEPÓSITO PROCESADO EXITOSAMENTE:')
            print(f'   Wallet: {wallet_address}')
            print(f'   Fichas anteriores: {current_chips}')
            print(f'   Fichas agregadas: {chips_to_add}')
            print(f'   Fichas totales: {new_chips}')
            print(f'   Transacción: {signature}')
            
        else:
            print(f'❌ ERROR: Usuario no encontrado con wallet {wallet_address}')
            
    except Exception as e:
        print(f'❌ ERROR al procesar depósito: {e}')
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == '__main__':
    process_manual_deposit()