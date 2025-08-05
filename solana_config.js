// Configuración para integración con Helius y Solana
const { Connection, PublicKey, Transaction, SystemProgram, LAMPORTS_PER_SOL } = require('@solana/web3.js');
const { Helius } = require('helius-sdk');

// Configuración de Helius
const HELIUS_API_KEY = process.env.HELIUS_API_KEY;
if (!HELIUS_API_KEY) {
    throw new Error('HELIUS_API_KEY environment variable not set');
}
const NETWORK = 'devnet'; // Cambiar a 'mainnet-beta' para producción

// Inicializar Helius
const helius = new Helius(HELIUS_API_KEY, NETWORK);

// Configuración de conexión RPC
const RPC_ENDPOINT = `https://${NETWORK}.helius-rpc.com/?api-key=${HELIUS_API_KEY}`;
const connection = new Connection(RPC_ENDPOINT, 'confirmed');

// Dirección del token de fichas del juego (se creará más adelante)
const GAME_TOKEN_MINT = null; // Se configurará después de crear el token

class SolanaGameIntegration {
    constructor() {
        this.helius = helius;
        this.connection = connection;
    }

    // Obtener balance de SOL de una wallet
    async getSOLBalance(walletAddress) {
        try {
            const publicKey = new PublicKey(walletAddress);
            const balance = await this.connection.getBalance(publicKey);
            return balance / LAMPORTS_PER_SOL;
        } catch (error) {
            console.error('Error obteniendo balance de SOL:', error);
            throw error;
        }
    }

    // Obtener todos los tokens de una wallet
    async getWalletTokens(walletAddress) {
        try {
            const response = await this.helius.rpc.getAssetsByOwner({
                ownerAddress: walletAddress,
                page: 1,
                limit: 1000
            });
            return response.items;
        } catch (error) {
            console.error('Error obteniendo tokens de wallet:', error);
            throw error;
        }
    }

    // Obtener balance de un token específico
    async getTokenBalance(walletAddress, tokenMint) {
        try {
            const tokens = await this.getWalletTokens(walletAddress);
            const gameToken = tokens.find(token => token.id === tokenMint);
            return gameToken ? gameToken.token_info?.balance || 0 : 0;
        } catch (error) {
            console.error('Error obteniendo balance de token:', error);
            return 0;
        }
    }

    // Validar que una wallet tiene suficientes fichas para apostar
    async validateBet(walletAddress, betAmount) {
        try {
            if (!GAME_TOKEN_MINT) {
                // Si no hay token personalizado, usar SOL
                const solBalance = await this.getSOLBalance(walletAddress);
                return solBalance >= betAmount;
            }
            
            const tokenBalance = await this.getTokenBalance(walletAddress, GAME_TOKEN_MINT);
            return tokenBalance >= betAmount;
        } catch (error) {
            console.error('Error validando apuesta:', error);
            return false;
        }
    }

    // Crear transacción para transferir fichas
    async createTransferTransaction(fromWallet, toWallet, amount) {
        try {
            const fromPublicKey = new PublicKey(fromWallet);
            const toPublicKey = new PublicKey(toWallet);
            
            if (!GAME_TOKEN_MINT) {
                // Transferir SOL
                const transaction = new Transaction().add(
                    SystemProgram.transfer({
                        fromPubkey: fromPublicKey,
                        toPubkey: toPublicKey,
                        lamports: amount * LAMPORTS_PER_SOL
                    })
                );
                
                const { blockhash } = await this.connection.getLatestBlockhash();
                transaction.recentBlockhash = blockhash;
                transaction.feePayer = fromPublicKey;
                
                return transaction;
            }
            
            // TODO: Implementar transferencia de tokens SPL
            throw new Error('Transferencia de tokens SPL no implementada aún');
        } catch (error) {
            console.error('Error creando transacción:', error);
            throw error;
        }
    }

    // Monitorear transacciones de una wallet
    async monitorWallet(walletAddress, callback) {
        try {
            // Configurar webhook para monitorear la wallet
            const webhook = await this.helius.createWebhook({
                webhookURL: 'https://your-app.com/webhook', // Cambiar por tu URL
                transactionTypes: ['Any'],
                accountAddresses: [walletAddress],
                webhookType: 'enhanced'
            });
            
            console.log('Webhook creado:', webhook);
            return webhook;
        } catch (error) {
            console.error('Error configurando monitoreo:', error);
            throw error;
        }
    }

    // Obtener historial de transacciones
    async getTransactionHistory(walletAddress, limit = 10) {
        try {
            const publicKey = new PublicKey(walletAddress);
            const signatures = await this.connection.getSignaturesForAddress(
                publicKey,
                { limit }
            );
            
            const transactions = [];
            for (const sig of signatures) {
                const tx = await this.connection.getTransaction(sig.signature);
                if (tx) {
                    transactions.push({
                        signature: sig.signature,
                        slot: tx.slot,
                        blockTime: tx.blockTime,
                        fee: tx.meta?.fee || 0
                    });
                }
            }
            
            return transactions;
        } catch (error) {
            console.error('Error obteniendo historial:', error);
            return [];
        }
    }
}

module.exports = {
    SolanaGameIntegration,
    helius,
    connection,
    NETWORK,
    HELIUS_API_KEY
};