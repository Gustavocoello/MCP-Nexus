/**
 * features/chat/utils/chatMemoryCache.jsx
 * Chat Memory Cache - Sistema de caché LRU para múltiples chats
 * Configuración optimizada: 5 chats × 5 mensajes = 25 mensajes totales en RAM
 */

import Logger from '../../../components/controller/log/logger';

const log = new Logger('chatMemoryCache');

class ChatMemoryCache {
  constructor(config = {}) {
    this._cache = new Map();
    this._maxChats = config.maxChats || 5;           // Máximo 5 chats
    this._messagesPerChat = config.messagesPerChat || 5; // Solo últimos 5 mensajes
    this._accessOrder = [];
  }
  keys() {
    return Array.from(this._cache.keys());
  }
  size() {
    return this._cache.size;
  }
  /** Verifica si un chat existe */
  has(chatId) {
    return this._cache.has(chatId);
  }
  set(chatId, messages) {
    if (!chatId) {
      log.warn('[ChatMemoryCache] chatId es requerido');
      return false;
    }
    
    if (!Array.isArray(messages)) {
      log.warn('[ChatMemoryCache] messages debe ser un array');
      return false;
    }

    /**
     * Guarda mensajes de un chat en caché
     * @param {string} chatId - ID del chat
     * @param {Array} messages - Array de mensajes
     * @returns {boolean}
     * @returns {Array} - Obtiene todos los IDs de chats almacenados
     */
    
    // Validar estructura de mensajes
    const validMessages = messages.filter(m => m && m.id);
    
    if (validMessages.length === 0) {
      log.warn('[ChatMemoryCache] No hay mensajes válidos para cachear');
      return false;
    }

    // Implementar LRU: si alcanzamos maxChats, eliminar el más antiguo
    if (this._cache.size >= this._maxChats && !this._cache.has(chatId)) {
      const oldest = this._accessOrder.shift();
      this._cache.delete(oldest);
      log.info(`[ChatMemoryCache] Removed oldest chat (${oldest}) - LRU cleanup`);
    }

    // Mantener solo los últimos N mensajes configurados
    const trimmedMessages = validMessages.slice(-this._messagesPerChat);

    // Guardar en caché
    this._cache.set(chatId, trimmedMessages);

    // Actualizar access order (LRU)
    this._accessOrder = this._accessOrder.filter(id => id !== chatId);
    this._accessOrder.push(chatId);

    log.info(
      `[ChatMemoryCache] Cached ${trimmedMessages.length}/${messages.length} messages for chat ${chatId}`
    );
    return true;
  }

  /**
   * Obtiene mensajes de un chat desde caché
   * @param {string} chatId
   * @returns {Array|null}
   */
  get(chatId) {
    if (!chatId) {
      log.warn('[ChatMemoryCache] chatId es requerido');
      return null;
    }

    if (!this._cache.has(chatId)) {
      return null;
    }

    // Actualizar access order (mover al final = más reciente)
    this._accessOrder = this._accessOrder.filter(id => id !== chatId);
    this._accessOrder.push(chatId);

    const messages = this._cache.get(chatId);
    log.info(`[ChatMemoryCache] Cache HIT - ${messages.length} messages for chat ${chatId}`);
    return messages;
  }

  /**
   * Elimina un chat de la caché
   * @param {string} chatId
   * @returns {boolean}
   */
  delete(chatId) {
    if (!chatId) return false;

    const existed = this._cache.delete(chatId);
    if (existed) {
      this._accessOrder = this._accessOrder.filter(id => id !== chatId);
      log.info(`[ChatMemoryCache] Deleted chat ${chatId}`);
    }
    return existed;
  }

  /**
   * Limpia toda la caché
   */
  clear() {
    const size = this._cache.size;
    this._cache.clear();
    this._accessOrder = [];
    log.info(`[ChatMemoryCache] Cleared ${size} chats from cache`);
  }

  /**
   * Tamaño actual de la caché
   */
  size() {
    return this._cache.size;
  }

  /**
   * Verifica si un chat existe en caché
   */
  has(chatId) {
    return this._cache.has(chatId);
  }

  /**
   * Obtiene estadísticas de la caché
   */
  getStats() {
    const totalMessages = Array.from(this._cache.values()).reduce(
      (sum, msgs) => sum + msgs.length,
      0
    );

    return {
      totalChats: this._cache.size,
      totalMessages,
      maxChats: this._maxChats,
      messagesPerChat: this._messagesPerChat,
      utilizationPercent: Math.round((this._cache.size / this._maxChats) * 100),
      oldestChat: this._accessOrder[0] || null,
      newestChat: this._accessOrder[this._accessOrder.length - 1] || null,
      estimatedRAM: `${Math.round((totalMessages * 2) / 1024)} KB` // ~2KB por mensaje
    };
  }

  /**
   * Debug info
   */
  /**
   * Debug info
   */
  debug() {
    // 1. Usamos logger.group y pasamos TODA la lógica dentro de la función flecha
    log.group('Debug Info', () => {
      log.table(this.getStats()); // Mostrar estadísticas
      log.debug('Access Order (LRU):', this._accessOrder); // Mostrar orden de acceso (LRU)
      const contentSummary = Array.from(this._cache.entries()).map(([id, msgs]) => ({
        chatId: id,
        messageCount: msgs.length,
        firstMsg: (msgs[0]?.content?.substring(0, 30) || '') + '...',
        lastMsg: (msgs[msgs.length - 1]?.content?.substring(0, 30) || '') + '...'
      }));

      // Mostrar contenidos en formato tabla (más limpio que un array de objetos)
      log.table(contentSummary);

    }); 
    // ¡Listo! El Logger ejecuta console.groupEnd() automáticamente aquí al cerrar la llave
  }
}

// Exportar instancia singleton con configuración optimizada
const chatMemoryCache = new ChatMemoryCache({
  maxChats: 5,           // Solo 5 chats en memoria
  messagesPerChat: 5     // Solo últimos 5 mensajes por chat
});

export default chatMemoryCache;