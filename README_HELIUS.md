# 🃏 La Más Alta Gana - Integración con Helius y Solana

## 🚀 Nueva Funcionalidad: Wallets de Solana

Este juego ahora incluye integración completa con la blockchain de Solana usando Helius como proveedor de RPC y APIs.

## 📋 Características de la Integración

### ✅ Funcionalidades Implementadas
- **Conexión de Wallets**: Phantom, Solflare, Backpack
- **Consulta de Balances**: SOL y tokens personalizados del juego
- **Historial de Transacciones**: Usando APIs de Helius
- **Validación de Wallets**: Verificación de direcciones válidas
- **Validación de Apuestas**: Verificar fondos suficientes
- **Interfaz de Usuario**: Página dedicada para gestión de wallets

### 🔄 Funcionalidades en Desarrollo
- **Transacciones de Apuestas**: Crear y firmar transacciones reales
- **Pagos de Premios**: Distribución automática de ganancias
- **Tokens del Juego**: Creación de token SPL personalizado
- **Webhooks**: Monitoreo en tiempo real de transacciones

## 🛠️ Configuración

### 1. Obtener API Key de Helius
1. Visita [helius.xyz](https://helius.xyz)
2. Crea una cuenta gratuita
3. Obtén tu API key del dashboard

### 2. Configurar Variables de Entorno
```bash
# Copia el archivo de ejemplo
cp .env.example .env

# Edita .env con tu API key
HELIUS_API_KEY=tu_api_key_real_aqui
HELIUS_NETWORK=devnet
```

### 3. Instalar Dependencias
```bash
# Dependencias de Python
pip install requests

# Dependencias de JavaScript (ya instaladas)
npm install @solana/web3.js helius-sdk
```

## 🎮 Cómo Usar

### Para Jugadores
1. **Acceder a Wallets**: Haz clic en "🔗 Conectar Wallet Solana" en el lobby
2. **Conectar Wallet**: Selecciona tu wallet preferida (Phantom, Solflare, etc.)
3. **Ver Balance**: Consulta tu SOL y fichas del juego
4. **Historial**: Revisa tus transacciones recientes
5. **Jugar**: Usa el botón "🎮 Jugar Ahora" para volver al juego

### Para Desarrolladores

#### Estructura de Archivos
```
├── helius_integration.py     # Backend de integración con Helius
├── templates/wallet.html     # Frontend de gestión de wallets
├── solana_config.js         # Configuración de Solana (frontend)
├── .env.example             # Plantilla de configuración
└── README_HELIUS.md         # Esta documentación
```

#### APIs Disponibles

**GET** `/api/wallet/balance/<wallet_address>`
- Obtiene balance de SOL y tokens del juego

**POST** `/api/wallet/validate`
- Valida una dirección de wallet
- Body: `{"wallet_address": "..."}`

**POST** `/api/wallet/bet/validate`
- Valida si una wallet puede apostar
- Body: `{"wallet_address": "...", "bet_amount": 100}`

**GET** `/api/wallet/transactions/<wallet_address>`
- Obtiene historial de transacciones
- Query params: `?limit=10`

## 🔧 Configuración Avanzada

### Redes de Solana
- **devnet**: Para desarrollo y pruebas (gratis)
- **mainnet**: Para producción (requiere SOL real)

### Tokens del Juego
Por defecto, el sistema busca un token personalizado. Para crear tu propio token:

1. Usa Solana CLI para crear un token SPL
2. Actualiza `GAME_TOKEN_MINT` en `.env`
3. Distribuye tokens iniciales a los jugadores

### Webhooks (Opcional)
Para monitoreo en tiempo real:

1. Configura `WEBHOOK_URL` en `.env`
2. Implementa el endpoint webhook en tu servidor
3. Usa `setup_webhook()` en `helius_integration.py`

## 🐛 Solución de Problemas

### Error: "Helius no disponible"
- Verifica que `HELIUS_API_KEY` esté configurada
- Confirma que la API key sea válida
- Revisa la conexión a internet

### Error: "Wallet no encontrada"
- Asegúrate de tener la wallet instalada en el navegador
- Verifica que la wallet esté desbloqueada
- Prueba con una wallet diferente

### Balances en 0
- En devnet, usa un faucet para obtener SOL de prueba
- Verifica que la dirección de wallet sea correcta
- Confirma que estés en la red correcta (devnet/mainnet)

## 📚 Recursos Adicionales

- [Documentación de Helius](https://docs.helius.xyz/)
- [Solana Web3.js](https://solana-labs.github.io/solana-web3.js/)
- [Phantom Wallet](https://phantom.app/)
- [Solflare Wallet](https://solflare.com/)
- [Backpack Wallet](https://backpack.app/)

## 🤝 Contribuir

Para contribuir a la integración de Solana:

1. Fork el repositorio
2. Crea una rama para tu feature
3. Implementa mejoras en `helius_integration.py` o `wallet.html`
4. Prueba con devnet
5. Envía un pull request

## 📄 Licencia

Este proyecto mantiene la misma licencia que el juego base.

---

**¡Disfruta jugando con criptomonedas reales en Solana! 🚀**