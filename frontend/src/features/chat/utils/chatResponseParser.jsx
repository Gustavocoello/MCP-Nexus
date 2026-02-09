// features/chat/utils/chatResponseParser.jsx
/**
 * Valida que un mensaje tenga la estructura correcta
 * @param {Object} msg - Mensaje a validar
 * @returns {boolean}
 */

import Logger from '../../../components/controller/log/logger';

const log = new Logger('chatResponseParser');

const isValidMessage = (msg) => {
  if (!msg || typeof msg !== 'object') {
    return false;
  }

  // Campos requeridos
  const hasId = msg.id !== undefined && msg.id !== null;
  const hasRole = msg.role && ['user', 'assistant', 'system'].includes(msg.role);
  const hasContent = msg.content !== undefined || msg.html !== undefined;

  return hasId && hasRole && hasContent;
};

/**
 * Normaliza un mensaje para tener estructura consistente
 * @param {Object} msg - Mensaje a normalizar
 * @returns {Object}
 */
const normalizeMessage = (msg) => {
  return {
    id: msg.id,
    role: msg.role,
    content: msg.content || '',
    html: msg.html || null,
    created_at: msg.created_at || msg.createdAt || new Date().toISOString(),
    updated_at: msg.updated_at || msg.updatedAt || null,
    // Campos opcionales
    hidden_context: msg.hidden_context || msg.hiddenContext || null,
    metadata: msg.metadata || null,
    // Flags
    streaming: msg.streaming || false,
    optimistic: msg.optimistic || false,
    partial: msg.partial || false
  };
};

/**
 * Parsea la respuesta del backend de mensajes
 * @param {any} data - Respuesta del backend (puede ser array, object, o null)
 * @param {number} limit - Límite de mensajes esperados (para calcular hasMore)
 * @returns {Object} - { messages: Array, hasMore: boolean, source: string }
 */
export const parseChatMessagesResponse = (data, limit = 20) => {
  // VALIDACIÓN 1: Verificar que data existe
  if (!data) {
    log.warn('[chatResponseParser] Respuesta vacía o null');
    return { 
      messages: [], 
      hasMore: false,
      source: 'empty',
      error: 'No data received'
    };
  }

  let rawMessages = [];
  let hasMore = false;
  let source = 'unknown';

  // CASO 1: data es un array directo
  if (Array.isArray(data)) {
    rawMessages = data;
    hasMore = data.length >= limit;
    source = 'array';
  } 
  // CASO 2: data.messages existe
  else if (data.messages && Array.isArray(data.messages)) {
    rawMessages = data.messages;
    // Preferir hasMore explícito del backend
    hasMore = Boolean(
      data.hasMore ?? 
      data.has_more ?? 
      (data.messages.length >= limit)
    );
    source = data.source || 'object.messages';
  } 
  // CASO 3: data.result.messages existe (formato anidado)
  else if (data.result?.messages && Array.isArray(data.result.messages)) {
    rawMessages = data.result.messages;
    hasMore = Boolean(
      data.result.hasMore ?? 
      data.result.has_more ?? 
      (data.result.messages.length >= limit)
    );
    source = data.result.source || 'object.result.messages';
  }
  // CASO 4: Formato desconocido
  else {
    log.warn('chatResponseParser] Formato de respuesta desconocido:', data);
    return { 
      messages: [], 
      hasMore: false,
      source: 'invalid',
      error: 'Unknown response format'
    };
  }

  // VALIDACIÓN 2: Filtrar y normalizar mensajes válidos
  const validMessages = rawMessages.filter(msg => {
    const valid = isValidMessage(msg);
    if (!valid) {
      log.warn('[chatResponseParser] Mensaje inválido descartado:', msg);
    }
    return valid;
  });

  // VALIDACIÓN 3: Si se perdieron mensajes en el filtrado, ajustar hasMore
  if (validMessages.length < rawMessages.length) {
    log.warn(
      `[chatResponseParser] Se descartaron ${rawMessages.length - validMessages.length} mensajes inválidos`
    );
    // Si había hasMore pero se filtraron mensajes, mantener hasMore
    hasMore = hasMore || (validMessages.length > 0);
  }

  // NORMALIZACIÓN: Asegurar estructura consistente
  const normalizedMessages = validMessages.map(normalizeMessage);

  // LOG INFORMATIVO
  log.info(
    `[chatResponseParser] Parsed ${normalizedMessages.length} messages ` +
    `(hasMore: ${hasMore}, source: ${source})`
  );

  return {
    messages: normalizedMessages,
    hasMore: hasMore && normalizedMessages.length > 0,
    source,
    totalRaw: rawMessages.length,
    totalValid: normalizedMessages.length
  };
};

/**
 * Helper: Parsea respuesta de un solo mensaje (para POST)
 * @param {Object} data - Respuesta con un mensaje
 * @returns {Object|null}
 */
export const parseSingleMessageResponse = (data) => {
  if (!data) {
    log.warn('[chatResponseParser] No message data received');
    return null;
  }

  // Si data ya es el mensaje
  if (isValidMessage(data)) {
    return normalizeMessage(data);
  }

  // Si data.message existe
  if (data.message && isValidMessage(data.message)) {
    return normalizeMessage(data.message);
  }

  // Si data.result.message existe
  if (data.result?.message && isValidMessage(data.result.message)) {
    return normalizeMessage(data.result.message);
  }

  log.warn('[chatResponseParser] Invalid message response:', data);
  return null;
};

/**
 * Helper: Valida respuesta de streaming
 * @param {Object} chunk - Chunk de streaming
 * @returns {boolean}
 */
export const isValidStreamingChunk = (chunk) => {
  if (!chunk || typeof chunk !== 'object') {
    return false;
  }

  // Debe tener al menos content o delta
  return (
    chunk.content !== undefined ||
    chunk.delta !== undefined ||
    chunk.text !== undefined
  );
};