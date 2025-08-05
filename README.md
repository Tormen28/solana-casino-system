# Juego de Cartas "La Más Alta Gana" con Integración de Solana

Este proyecto es una aplicación web de un juego de cartas multijugador. Se integra con la blockchain de Solana para permitir a los jugadores depositar SOL, que se convierten en "fichas" internas para jugar. Los jugadores también pueden retirar sus fichas, que se convierten de nuevo a SOL.

## Características

-   Juego de cartas "La Más Alta Gana" en tiempo real con WebSockets.
-   Soporte para jugadores humanos y bots.
-   **Depósitos y Retiros en SOL**: Los jugadores pueden depositar SOL desde su propia wallet. El sistema verifica la transacción y acredita una cantidad equivalente de fichas de juego (a una tasa de 1 SOL = 100,000 fichas).
-   **Retiros a Wallet Personal**: Los jugadores pueden retirar sus fichas, que se convierten de nuevo a SOL y se envían a su wallet, con una pequeña comisión de transacción.
-   Sistema de perfiles de usuario y persistencia de datos con SQLite.
-   Servidor de producción basado en Waitress.

## Requisitos Previos

-   Python 3.9+
-   Node.js y npm
-   Una wallet de Solana con fondos en la Devnet.

## Configuración del Entorno

1.  **Clonar el repositorio:**

    ```bash
    git clone <URL_DEL_REPOSITORIO>
    cd idea
    ```

2.  **Crear y activar un entorno virtual de Python:**

    ```bash
    python -m venv venv
    # En Windows
    .\venv\Scripts\Activate.ps1
    # En macOS/Linux
    source venv/bin/activate
    ```

3.  **Instalar las dependencias de Python:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Instalar las dependencias de Node.js:**

    ```bash
    npm install
    ```

5.  **Configurar las variables de entorno:**

    Crea un archivo llamado `.env` en la raíz del proyecto y añade las siguientes variables:

    ```env
    # Clave secreta para Flask (puedes generar una con `openssl rand -hex 32`)
    SECRET_KEY='tu_clave_secreta_aqui'

    # API Key de Helius para interactuar con Solana
    HELIUS_API_KEY='tu_api_key_de_helius'

    # Red de Solana a utilizar (mainnet-beta o devnet)
    HELIUS_NETWORK='devnet'

    # Dirección de la wallet que recibirá los depósitos (tu wallet de Solana)
    CUSTODIAL_ADDRESS='tu_direccion_de_wallet_de_solana'

    # Dirección de la wallet de la tesorería del juego (donde se envían los depósitos)
    GAME_TREASURY='tu_direccion_de_wallet_de_tesoreria'

    # Semilla de la wallet custodial (para procesar los retiros)
    # IMPORTANTE: Mantén esto seguro y nunca lo compartas.
    CUSTODIAL_WALLET_SEED='tu_frase_semilla_de_12_o_24_palabras'
    ```

## Ejecución de la Aplicación

Para iniciar el servidor en modo de producción, ejecuta:

```bash
python app.py
```

El servidor estará disponible en `http://localhost:8080`.

## Estructura del Proyecto

-   `app.py`: Lógica principal del backend de Flask, WebSockets y el juego.
-   `helius_integration.py`: Módulo para la comunicación con la API de Helius.
-   `requirements.txt`: Dependencias de Python.
-   `package.json`: Dependencias de Node.js.
-   `templates/`: Plantillas HTML de la aplicación.
-   `game.db`: Base de datos SQLite.
-   `.env`: Archivo de variables de entorno (no incluido en el repositorio).